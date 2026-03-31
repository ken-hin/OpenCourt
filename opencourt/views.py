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
from datetime import date, timedelta
from django.db import models
from django.db.models import Prefetch, Q, Count, Avg, Sum
from django.views.generic import TemplateView, ListView
from django.db.models import Case, When, Value, OuterRef, Subquery, FloatField, F, ExpressionWrapper
from django.shortcuts import get_object_or_404
from opencourt.models import Team, Conference, TeamSeasonStats, Game, GameTeamStats, Ranking


class HomeView(TemplateView):
    """Landing page with featured teams, conferences, and stats."""
    template_name = 'opencourt/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get top 5 teams by win percentage
        top_teams = Team.objects.filter(
            season_stats__season=2024  # Current season
        ).select_related('conference').prefetch_related(
            Prefetch('season_stats', queryset=TeamSeasonStats.objects.filter(season=2024), to_attr='_current_stats')
        ).order_by('-season_stats__win_pct')[:5]

        # Get all conferences with team counts
        conferences = Conference.objects.annotate(
            team_count=Count('teams', distinct=True)
        ).order_by('-team_count')[:8]  # Top 8 by team count

        # Get some overall stats
        total_teams = Team.objects.count()
        total_conferences = Conference.objects.count()

        context.update({
            'top_teams': top_teams,
            'conferences': conferences,
            'total_teams': total_teams,
            'total_conferences': total_conferences,
        })

        return context


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
      - prefetch_related('teams') with ordering by win_pct descending for conference rankings
      - Prefetch('teams__season_stats', ..., to_attr='_current_stats') loads
        only the current season's stats for every team in a single query.
        This feeds the Team.current_season property so the template can
        access {{ team.current_season.wins }} without any additional DB hits.
      - Annotations for conference stats: team_count, avg_win_pct, total_wins, total_losses

    The template filters out conferences with 0 teams (non-D1 or empty
    conferences that came from the API) using {% if conference.teams.count > 0 %}.
    """
    model = Conference
    template_name = 'opencourt/conferences.html'

    def get_queryset(self):
      current_year = date.today().year
      return Conference.objects.prefetch_related(
        Prefetch(
          'teams',
          queryset=Team.objects.annotate(
            current_win_pct=Subquery(
              TeamSeasonStats.objects.filter(team=OuterRef('pk'), season=current_year).values('win_pct')[:1],
              output_field=FloatField()
            )
          ).order_by('-current_win_pct'),
        ),
        Prefetch(
          'teams__season_stats',
          queryset=TeamSeasonStats.objects.filter(season=current_year),
          to_attr='_current_stats'
        )
      ).annotate(
        team_count=Count('teams', distinct=True),
        avg_win_pct=Avg('teams__season_stats__win_pct', filter=Q(teams__season_stats__season=current_year), distinct=True),
        total_wins=Sum('teams__season_stats__wins', filter=Q(teams__season_stats__season=current_year), distinct=True),
        total_losses=Sum('teams__season_stats__losses', filter=Q(teams__season_stats__season=current_year), distinct=True),
      ).all()

class RankingsListView(TemplateView):
    """
    Renders dual-poll rankings page (AP Top 25 + Coaches Poll side by side)
    with week-by-week navigation via ?week=N query parameter.

    Defaults to the most recent week when no parameter is provided.

    Template: rankings.html
    Context variables:
      ap_rankings       — Ranking queryset for the selected week's AP poll
      coaches_rankings  — Ranking queryset for the selected week's Coaches Poll
      ap_poll_date      — datetime of the selected AP poll week
      coaches_poll_date — datetime of the selected Coaches Poll week
      available_weeks   — list of dicts [{week, poll_date}, ...] for the week
                          dropdown, ordered newest-first
      selected_week     — int, the currently displayed week number
      conference_list   — all conferences for the filter dropdown
    """

    template_name = 'opencourt/rankings.html'

    def _ranked_teams(self, poll_type, week=None):
        """
        Return (poll_date, queryset) for a given poll_type and week in the
        current season. If week is None, returns the most recent week.
        """
        current_year = date.today().year
        base_qs = Ranking.objects.filter(poll_type=poll_type, season=current_year)

        if week is not None:
            poll_date = base_qs.filter(week=week).values_list('poll_date', flat=True).first()
        else:
            poll_date = base_qs.order_by('-poll_date').values_list('poll_date', flat=True).first()

        if not poll_date:
            return None, Ranking.objects.none()

        # Subquery helper for the most recent season stats row per team.
        latest_stats = (
            TeamSeasonStats.objects
            .filter(team=OuterRef('team__pk'))
            .order_by('-season')
        )
        def latest(field_name):
            return Subquery(latest_stats.values(field_name)[:1], output_field=FloatField())

        qs = (
            Ranking.objects
            .filter(poll_type=poll_type, poll_date=poll_date, ranking__gte=1, ranking__lte=25)
            .select_related('team', 'team__conference')
            .annotate(
                latest_wins=latest('wins'),
                latest_losses=latest('losses'),
                latest_off_points=latest('off_points'),
                latest_opp_points=latest('opp_points'),
            )
            .annotate(
                latest_point_margin=ExpressionWrapper(
                    F('latest_off_points') - F('latest_opp_points'),
                    output_field=FloatField(),
                )
            )
            .order_by('ranking')
        )

        return poll_date, qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_year = date.today().year

        # Build available weeks list for the dropdown (newest first).
        available_weeks = list(
            Ranking.objects
            .filter(poll_type="AP Top 25", season=current_year)
            .values('week', 'poll_date')
            .distinct()
            .order_by('-week')
        )

        # Read ?week= param, default to most recent week.
        selected_week = self.request.GET.get('week')
        if selected_week is not None:
            try:
                selected_week = int(selected_week)
            except (ValueError, TypeError):
                selected_week = None
        if selected_week is None and available_weeks:
            selected_week = available_weeks[0]['week']

        ap_date, ap_qs = self._ranked_teams("AP Top 25", week=selected_week)
        coaches_date, coaches_qs = self._ranked_teams("Coaches Poll", week=selected_week)

        context['ap_rankings'] = ap_qs
        context['coaches_rankings'] = coaches_qs
        context['ap_poll_date'] = ap_date
        context['coaches_poll_date'] = coaches_date
        context['available_weeks'] = available_weeks
        context['selected_week'] = selected_week
        context['conference_list'] = Conference.objects.order_by('abbrv')
        return context

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
    """
    Upcoming games page with head-to-head stat comparison.

    Template: opencourt/head_head.html

    URL params:
      ?date=YYYY-MM-DD  — filter games to a specific date (defaults to today)
      ?date=all         — show every future scheduled game in chronological order

    Context variables:
      games           — enriched list of dicts for the selected date (or all
                        dates if show_all=True). Used by the main #games-list.
      all_games       — enriched list of ALL future scheduled games in order.
                        Always passed regardless of selected tab. Used by the
                        hidden #search-results pool so the search input can
                        find any team across the full schedule without a reload.
      show_all        — bool, True when ?date=all was requested. The template
                        uses this to highlight the "Show All" tab and adjust
                        the page subtitle.
      upcoming_dates  — list of date objects for the next 7 days, for the tabs.
      selected_date   — the date currently being viewed (None when show_all).
      today           — date.today() so the template can label the first tab.
      tomorrow        — today + 1 day for the second tab label.

    Query optimizations:
      select_related('home_team', 'away_team') avoids FK hits per game.
      Two Prefetch calls bulk-load each team's current-season stats so
      Team.current_season never fires individual queries inside the loop.
    """
    template_name = 'opencourt/head_head.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        today    = date.today()
        tomorrow = today + timedelta(days=1)

        # 7-day window for the tab bar
        upcoming_dates = [today + timedelta(days=i) for i in range(7)]

        # Determine whether "Show All" was requested
        date_param = self.request.GET.get('date', str(today))
        show_all   = (date_param == 'all')

        if show_all:
            selected_date = None
        else:
            try:
                selected_date = date.fromisoformat(date_param)
            except ValueError:
                selected_date = today

        current_year = date.today().year

        # ── Shared prefetch setup ────────────────────────────────────────
        # Both querysets use the same select_related + Prefetch structure.
        # Defined once here to keep things DRY.
        def base_qs():
            return (
                Game.objects
                .filter(status="scheduled")
                .select_related('home_team', 'away_team')
                .prefetch_related(
                    Prefetch(
                        'home_team__season_stats',
                        queryset=TeamSeasonStats.objects.filter(season=current_year),
                        to_attr='_current_stats',
                    ),
                    Prefetch(
                        'away_team__season_stats',
                        queryset=TeamSeasonStats.objects.filter(season=current_year),
                        to_attr='_current_stats',
                    ),
                )
                .order_by('start_date')
            )

        # ── Per-game average helpers ─────────────────────────────────────
        def avg(stat_obj, field):
            """Divide a season total by games played → per-game average."""
            if stat_obj is None:
                return None
            total       = getattr(stat_obj, field, None)
            games_played = getattr(stat_obj, 'games', None)
            if total and games_played:
                return round(total / games_played, 1)
            return None

        def pct(stat_obj, field):
            """Round a field already stored as a percentage (e.g. 46.3)."""
            if stat_obj is None:
                return None
            val = getattr(stat_obj, field, None)
            return round(val, 1) if val is not None else None

        # ── Enrich a queryset into the template-friendly list of dicts ───
        def enrich(qs):
            result = []
            for game in qs:
                hs  = game.home_team.current_season   # TeamSeasonStats or None
                as_ = game.away_team.current_season
                result.append({
                    'game':      game,
                    'home_team': game.home_team,
                    'away_team': game.away_team,
                    'home_stats': {
                        'pts':  avg(hs,  'off_points'),
                        'fgp':  pct(hs,  'off_fg_pct'),
                        'tpp':  pct(hs,  'off_3pt_pct'),
                        'ftp':  pct(hs,  'off_ft_pct'),
                        'reb':  avg(hs,  'off_reb_total'),
                        'oreb': avg(hs,  'off_reb_offensive'),
                        'ast':  avg(hs,  'off_assists'),
                        'stl':  avg(hs,  'off_steals'),
                        'blk':  avg(hs,  'off_blocks'),
                        'tov':  avg(hs,  'off_turnovers'),
                    },
                    'away_stats': {
                        'pts':  avg(as_, 'off_points'),
                        'fgp':  pct(as_, 'off_fg_pct'),
                        'tpp':  pct(as_, 'off_3pt_pct'),
                        'ftp':  pct(as_, 'off_ft_pct'),
                        'reb':  avg(as_, 'off_reb_total'),
                        'oreb': avg(as_, 'off_reb_offensive'),
                        'ast':  avg(as_, 'off_assists'),
                        'stl':  avg(as_, 'off_steals'),
                        'blk':  avg(as_, 'off_blocks'),
                        'tov':  avg(as_, 'off_turnovers'),
                    },
                })
            return result

        # ── Build the two querysets ──────────────────────────────────────
        # all_future_qs: every scheduled game from today forward.
        #   Always computed — feeds both all_games (for search) and
        #   games when show_all=True.
        all_future_qs = base_qs().filter(start_date__gte=today)

        if show_all:
            games_qs = all_future_qs
        else:
            games_qs = base_qs().filter(start_date__date=selected_date)

        # Enrich both. all_games is always the full future schedule so search
        # works regardless of which date tab the user has open.
        all_games = enrich(all_future_qs)
        games     = enrich(games_qs)

        context['games']          = games
        context['all_games']      = all_games
        context['show_all']       = show_all
        context['upcoming_dates'] = upcoming_dates
        context['selected_date']  = selected_date
        context['today']          = today
        context['tomorrow']       = tomorrow
        return context