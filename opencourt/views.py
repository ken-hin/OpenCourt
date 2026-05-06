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
#
# ─────────────────────────────────────────────────────────────────────────
# UpcomingView — Predictions page architecture
# ─────────────────────────────────────────────────────────────────────────
# The /upcoming/ URL is a single dispatcher view that renders one of two
# templates depending on the ?view= query parameter:
#
#     ?view=calendar (default) → opencourt/predictions_calendar.html
#                                month grid, color-coded by prediction outcome
#     ?view=list               → opencourt/head_head.html
#                                head-to-head card grid + global search pool
#
# UpcomingView.get_template_names() picks the template; get_context_data()
# delegates to _build_calendar_context() or _build_list_context(). Both
# branches share:
#   - _get_predict_model()             — process-cached XGBoost / sklearn model
#   - _batch_predict_home_wins(games)  — single-call batched prediction
#   - _current_season_year()           — date → season-year resolver
#   - the season-accuracy cache (warmed by CacheWarmerMiddleware)
#
# Season-year convention. The DB stores `Game.season` and
# `TeamSeasonStats.season` as the season's ENDING calendar year (so
# season=2026 is the 2025-26 season). Both view branches must compute
# season_year using the same formula or their prefetched team stats
# diverge for the same game and predictions disagree across views.
# Calendar uses (year, month) from URL params; list uses today. They
# call the same per-date formula:  month >= 7 ? year+1 : year.
#
# Calendar pill states. Each game on the calendar gets one of:
#     correct        — model picked the actual home/away winner       (green)
#     incorrect      — model picked the wrong team                    (red)
#     unplayed       — game scheduled, not yet final                  (neutral)
#     no_prediction  — game played but feature stats were missing     (neutral)
# Days with more than CAL_PILL_CAP games collapse the overflow into a
# "+N more" pill that opens a modal containing full head-to-head cards.
#
# List view search. A single season-wide query feeds both the visible
# (paginated/date-filtered) `games` list and a global `all_games` pool.
# The pool is what the search bar filters — typing a team reveals every
# matching game in the current season (played + upcoming), regardless of
# which paginated page the user is currently on.

import calendar
import json
import logging
import threading
from collections import defaultdict
from datetime import date, datetime, timedelta
from math import floor

import numpy as np
import pandas as pd
from django.db.models import (Avg, Case, Count, ExpressionWrapper, F, FloatField, OuterRef, Prefetch, Q, Subquery, Sum, When)
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.generic import ListView, TemplateView
from django.core.paginator import Paginator
from django.core.cache import cache

from opencourt.models import Conference, Game, GameTeamStats, Ranking, Team, TeamSeasonStats
from opencourt.predictions.predict import DEFAULT_MODEL as PREDICT_MODEL_PATH
from opencourt.predictions.features import build_features
import joblib

logger = logging.getLogger(__name__)

# Module-level prediction-model cache. joblib.load on the .pkl takes ~50-200ms
# and was previously being called once per game inside predict_game() — for a
# season with ~5,000 completed games that alone runs the request past the
# gunicorn worker timeout. We load lazily on first use, then reuse the same
# in-memory model for every subsequent request handled by this worker.
_PREDICT_MODEL = None
_PREDICT_MODEL_LOAD_FAILED = False

def _get_predict_model():
    """Return a process-cached prediction model, or None if loading failed."""
    global _PREDICT_MODEL, _PREDICT_MODEL_LOAD_FAILED
    if _PREDICT_MODEL is not None:
        return _PREDICT_MODEL
    if _PREDICT_MODEL_LOAD_FAILED:
        return None
    try:
        _PREDICT_MODEL = joblib.load(PREDICT_MODEL_PATH)
    except Exception:
        logger.exception("Failed to load prediction model from %s", PREDICT_MODEL_PATH)
        _PREDICT_MODEL_LOAD_FAILED = True
        return None
    return _PREDICT_MODEL

def _predict_home_win(pred_model, h_stats, a_stats, home_adv):
    """
    Single-game prediction helper. Returns True/False for home win, or None
    if features can't be built (missing stats / divide-by-zero).
    """
    if pred_model is None or h_stats is None or a_stats is None:
        return None
    try:
        features = build_features(h_stats, a_stats, home_adv)
        pred = pred_model.predict(features)
    except (TypeError, ZeroDivisionError):
        return None
    if not isinstance(pred, np.ndarray) or len(pred) == 0:
        return None
    return bool(pred[0] == 1)

# ── Cache warmer for season-wide model accuracy ──────────────────────────────
# The /upcoming/?mode=results page shows a banner with prediction accuracy
# across every completed game this season. Even after vectorizing predictions
# the cold-cache compute is ~1-2s on Railway. Rather than make a user wait for
# it, the CacheWarmerMiddleware fires `trigger_async_warm()` on the first
# request to any page so the cache is already populated by the time someone
# clicks through to results. LocMemCache is per-worker, so each gunicorn
# worker warms its own copy once. The threading.Lock + in-flight set prevent
# duplicate warms within a single worker if multiple requests race in.

ACCURACY_CACHE_KEY = 'season_accuracy_{season_year}'
_warm_lock = threading.Lock()
_warm_in_flight = set()

def _current_season_year():
    """
    Return the `season` value of the CBB season "today" belongs to.

    Important: despite what some model docstrings say, the actual data in
    this DB stores Game.season / TeamSeasonStats.season as the season's
    **ending** calendar year. So Game.season=2026 paired with
    season_label='20252026' is the 2025-26 season. The formula below
    follows that convention:
      • month >= 7 (Jul-Dec, fall semester): we're inside (or about to
        start) a season ending NEXT calendar year. → today.year + 1
      • month <  7 (Jan-Jun, spring semester): we're inside (or just past)
        a season ending THIS calendar year.       → today.year

    Both UpcomingView's calendar branch and list branch use this — and
    the calendar's per-month formula must match this convention too —
    otherwise prefetches would target the wrong season's stats and the
    same game could produce different predictions in each view.
    """
    today = date.today()
    return today.year + 1 if today.month >= 7 else today.year

def _finished_games_qs(season_year):
    """Queryset of finished games for the given season with stats prefetched.

    Mirrors the prefetch shape used by UpcomingView.base_qs so that
    `g.home_team.current_season` (the prefetched _current_stats attr) hits
    cache instead of issuing a query per game.
    """
    return (
        Game.objects
        .filter(status="final", home_winner__isnull=False, season=season_year)
        .select_related('home_team', 'away_team')
        .prefetch_related(
            Prefetch(
                'home_team__season_stats',
                queryset=TeamSeasonStats.objects.filter(season=season_year),
                to_attr='_current_stats',
            ),
            Prefetch(
                'away_team__season_stats',
                queryset=TeamSeasonStats.objects.filter(season=season_year),
                to_attr='_current_stats',
            ),
        )
    )

def _compute_season_accuracy(season_finished_qs, pred_model):
    """
    Compute prediction accuracy across every completed game in the
    provided queryset using a single vectorized predict() call.

    Returns: {'correct': int, 'total': int, 'pct': float}
    """
    empty = {'correct': 0, 'total': 0, 'pct': 0}
    if pred_model is None:
        return empty

    feature_rows = []
    actuals = []
    for g in season_finished_qs:
        h_stats = g.home_team.current_season
        a_stats = g.away_team.current_season
        if not (h_stats and a_stats):
            continue
        home_adv = 0 if g.neutral_site else 1
        # Inline the feature math so we avoid building one DataFrame per game.
        # If any stat is missing, TypeError fires here and we skip the game.
        try:
            row = {
                'diff_efg_pct': h_stats.off_eff_fg_pct - a_stats.off_eff_fg_pct,
                'diff_turnover_rate': (
                    (h_stats.off_turnovers / h_stats.off_possessions)
                    - (a_stats.off_turnovers / a_stats.off_possessions)
                ),
                'diff_point_diff': (
                    (h_stats.off_points - h_stats.opp_points)
                    - (a_stats.off_points - a_stats.opp_points)
                ),
                'diff_pace': h_stats.pace - a_stats.pace,
                'diff_avg_ftr': h_stats.off_ft_rate - a_stats.off_ft_rate,
                'diff_avg_rating': h_stats.off_rating - a_stats.off_rating,
                'diff_avg_blocks': h_stats.off_blocks - a_stats.off_blocks,
                'diff_avg_oreb_pct': h_stats.off_oreb_pct - a_stats.off_oreb_pct,
                'diff_avg_ato_rto': (
                    (h_stats.off_assists / h_stats.off_turnovers)
                    - (a_stats.off_assists / a_stats.off_turnovers)
                ),
                'home_advantage': home_adv,
            }
        except (TypeError, ZeroDivisionError):
            continue
        feature_rows.append(row)
        actuals.append(bool(g.home_winner))

    if not feature_rows:
        return empty

    # Single batched predict() call — the big win versus a per-game loop.
    try:
        features_df = pd.DataFrame(feature_rows)
        preds = pred_model.predict(features_df)
    except Exception:
        logger.exception("Batched season accuracy prediction failed")
        return empty

    actuals_arr = np.asarray(actuals, dtype=bool)
    pred_home_win = np.asarray(preds) == 1
    correct = int(np.sum(pred_home_win == actuals_arr))
    total = int(actuals_arr.size)
    return {
        'correct': correct,
        'total': total,
        'pct': round(correct / total * 100, 1) if total else 0,
    }

def _batch_predict_home_wins(games, pred_model):
    """
    Run predictions in a single batched predict() call for many games.

    Returns: {game_id: bool}  — True if home team predicted to win,
                               False if away team predicted to win.
    Games with missing stats / divide-by-zero are silently skipped (no key).
    """
    if pred_model is None:
        return {}

    feature_rows = []
    game_ids = []
    for g in games:
        h_stats = g.home_team.current_season
        a_stats = g.away_team.current_season
        if not (h_stats and a_stats):
            continue
        home_adv = 0 if g.neutral_site else 1
        try:
            row = {
                'diff_efg_pct': h_stats.off_eff_fg_pct - a_stats.off_eff_fg_pct,
                'diff_turnover_rate': (
                    (h_stats.off_turnovers / h_stats.off_possessions)
                    - (a_stats.off_turnovers / a_stats.off_possessions)
                ),
                'diff_point_diff': (
                    (h_stats.off_points - h_stats.opp_points)
                    - (a_stats.off_points - a_stats.opp_points)
                ),
                'diff_pace': h_stats.pace - a_stats.pace,
                'diff_avg_ftr': h_stats.off_ft_rate - a_stats.off_ft_rate,
                'diff_avg_rating': h_stats.off_rating - a_stats.off_rating,
                'diff_avg_blocks': h_stats.off_blocks - a_stats.off_blocks,
                'diff_avg_oreb_pct': h_stats.off_oreb_pct - a_stats.off_oreb_pct,
                'diff_avg_ato_rto': (
                    (h_stats.off_assists / h_stats.off_turnovers)
                    - (a_stats.off_assists / a_stats.off_turnovers)
                ),
                'home_advantage': home_adv,
            }
        except (TypeError, ZeroDivisionError):
            continue
        feature_rows.append(row)
        game_ids.append(g.id)

    if not feature_rows:
        return {}

    try:
        features_df = pd.DataFrame(feature_rows)
        preds = pred_model.predict(features_df)
    except Exception:
        logger.exception("Batched calendar prediction failed")
        return {}

    return {gid: bool(p == 1) for gid, p in zip(game_ids, np.asarray(preds))}

def _warm_season_accuracy(season_year=None):
    """Synchronously recompute season accuracy and write it to the cache.

    Returns the accuracy dict. Called both as the cache-miss fallback inside
    UpcomingView and from the background warmer thread.
    """
    if season_year is None:
        season_year = _current_season_year()

    pred_model = _get_predict_model()
    qs = _finished_games_qs(season_year)
    accuracy = _compute_season_accuracy(qs, pred_model)

    # Cache successful results for 1 hour. Cache empty results for 60s so we
    # don't hammer a broken model on every request but recover quickly.
    ttl = 60 * 60 if accuracy.get('total') else 60
    cache.set(ACCURACY_CACHE_KEY.format(season_year=season_year), accuracy, ttl)
    return accuracy

def _warm_target(season_year):
    """Thread entry point — runs the warm and cleans up its DB connection."""
    from django.db import connection
    try:
        accuracy = _warm_season_accuracy(season_year)
        logger.info(
            "Warmed season_accuracy_%s in background: %s/%s correct (%s%%)",
            season_year, accuracy.get('correct'), accuracy.get('total'),
            accuracy.get('pct'),
        )
    except Exception:
        logger.exception("Cache warmer failed for season %s", season_year)
    finally:
        with _warm_lock:
            _warm_in_flight.discard(season_year)
        # Threads get their own DB connection from Django's connection pool;
        # close it explicitly so it doesn't leak when the thread exits.
        connection.close()

def trigger_async_warm(season_year=None):
    """Fire-and-forget: spawn a daemon thread to warm the accuracy cache.

    No-op if the cache is already populated, or if a warm for this season
    is already in flight in this worker. Returns True if a thread was spawned.
    """
    if season_year is None:
        season_year = _current_season_year()

    if cache.get(ACCURACY_CACHE_KEY.format(season_year=season_year)) is not None:
        return False

    with _warm_lock:
        if season_year in _warm_in_flight:
            return False
        _warm_in_flight.add(season_year)

    t = threading.Thread(
        target=_warm_target,
        args=(season_year,),
        name=f'season-accuracy-warmer-{season_year}',
        daemon=True,
    )
    t.start()
    return True

class HomeView(TemplateView):
    template_name = 'opencourt/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_year = date.today().year

        # Get top 5 teams entirely in the database — no Python sorting
        top_team_ids = (
            TeamSeasonStats.objects.filter(season=current_year, win_pct__isnull=False).order_by('-win_pct').values_list('team_id', flat=True)[:5]
        )

        # Preserve the ordering from the subquery
        preserved_order = Case(
            *[When(pk=pk, then=pos) for pos, pk in enumerate(top_team_ids)]
        )

        context['top_teams'] = (
            Team.objects.filter(pk__in=top_team_ids).select_related('conference').prefetch_related(
                Prefetch(
                    'season_stats',
                    queryset=TeamSeasonStats.objects.filter(season=current_year),
                    to_attr='_current_stats',
                )
            ).order_by(preserved_order)
        )

        context['conferences'] = Conference.objects.all().order_by('name')[:3]

        # Use.count() — single query each, not loading all objects
        context['total_teams'] = Team.objects.count()
        context['total_conferences'] = Conference.objects.count()
        context['total_games'] = (Game.objects.filter(season=current_year).count())

        return context

class AboutView(TemplateView):
    """Static about/info page. No model data needed."""
    template_name = 'opencourt/about.html'

class TeamListView(ListView):
    model = Team
    template_name = 'opencourt/teams.html'

    def get_queryset(self):
        current_year = date.today().year

        qs = (
            Team.objects.select_related('conference').prefetch_related(
                Prefetch(
                    'season_stats',
                    queryset=TeamSeasonStats.objects.filter(season=current_year),
                    to_attr='_current_stats',
                )
            ).order_by('school')
        )

        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(
                Q(school__icontains=q) |
                Q(mascot__icontains=q) |
                Q(display_name__icontains=q)
            )
        return qs

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
      ap_rankings — Ranking queryset for the selected week's AP poll
      coaches_rankings — Ranking queryset for the selected week's Coaches Poll
      ap_poll_date — datetime of the selected AP poll week
      coaches_poll_date — datetime of the selected Coaches Poll week
      available_weeks — list of dicts [{week, poll_date}, ...] for the week
                        dropdown, ordered newest-first
      selected_week — int, the currently displayed week number
      conference_list — all conferences for the filter dropdown
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
      team — the Team model instance (for name, colors, venue, etc.)
      season_stats — raw QuerySet list for any template-side iteration
      schedule — pre-processed list of dicts for the current season game table.

        Each dict contains:
          game — Game object (date, venue, scores, etc.)
          is_home — bool, True if this team was home
          opponent — Team object for the other side
          team_points — int, this team's final score
          opp_points — int, opponent's final score
          won — bool, True if this team won
          home_stats — GameTeamStats for the home team (or None)
          away_stats — GameTeamStats for the away team (or None)
        Home/away logic is resolved here so the template doesn't need to branch on
        home_team vs away_team. Box score stats are prefetched via Prefetch('team_stats')
        and split into home_stats / away_stats by matching team_id against the Game's home_team_id.

      stat_years — JSON array of season labels, used as chart x-axis categories
      wins/losses — JSON arrays of per-season win/loss counts
      win_pct — JSON array of win percentages (0-100 scale)
      off_rtg — JSON array of offensive ratings (points per 100 possessions)
      opp_rtg — JSON array of defensive ratings (points allowed per 100 poss.)
      eff_fg — JSON array of effective FG% (Four Factors: shooting)
      to_ratio — JSON array of turnover ratio (Four Factors: ball security)
      oreb_pct — JSON array of offensive rebound % (Four Factors: rebounding)
      ft_rate — JSON array of free throw rate (Four Factors: free throws)
      3pt_pct — JSON array of 3-point shooting percentage
      off_pts — JSON array of points scored per game
      opp_pts — JSON array of points allowed per game

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
        wins = [int(s.wins) if s.wins is not None else None for s in season_stats]
        losses = [int(s.losses) if s.losses is not None else None for s in season_stats]
        win_pct = [round(s.win_pct, 1) if s.win_pct else None for s in season_stats]

        # Efficiency ratings (tempo-independent, best for cross-team comparison)
        off_rating = [round(s.off_rating, 1) if s.off_rating else None for s in season_stats]
        opp_rating = [round(s.opp_rating, 1) if s.opp_rating else None for s in season_stats]

        # Four Factors — the core predictive metrics in basketball analytics
        off_eff_fg_pct = [round(s.off_eff_fg_pct, 1) if s.off_eff_fg_pct else None for s in season_stats]
        off_to_ratio = [round(s.off_turnover_ratio*100, 1) if s.off_turnover_ratio else None for s in season_stats]
        off_oreb_pct = [round(s.off_oreb_pct, 1) if s.off_oreb_pct else None for s in season_stats]
        off_ft_rate = [round(s.off_ft_rate, 1)  if s.off_ft_rate else None for s in season_stats]

        # Additional shooting & scoring (extend as the team view is built out)
        off_fg_pct = [round(s.off_fg_pct, 1) if s.off_fg_pct else None for s in season_stats]
        off_3pt_pct = [round(s.off_3pt_pct, 1) if s.off_3pt_pct else None for s in season_stats]
        off_ft_pct = [round(s.off_ft_pct, 1) if s.off_ft_pct else None for s in season_stats]
        off_pts = [round(s.off_points / s.games, 1) if s.off_points and s.games else None for s in season_stats]
        opp_pts = [round(s.opp_points / s.games, 1) if s.opp_points and s.games else None for s in season_stats]

        context['team'] = team
        context['season_stats'] = season_stats
        context['stat_years'] = json.dumps(season_labels)

        # Calculate per-game averages for current season display
        current_stats = team.current_season
        if current_stats and current_stats.games:
            context['current_ppg'] = round(current_stats.off_points / current_stats.games, 1) if current_stats.off_points else None
            context['current_rpg'] = round(current_stats.off_reb_total / current_stats.games, 1) if current_stats.off_reb_total else None
            context['current_apg'] = round(current_stats.off_assists / current_stats.games, 1) if current_stats.off_assists else None
            context['current_topg'] = round(current_stats.off_turnovers / current_stats.games, 1) if current_stats.off_turnovers else None
            context['current_spg'] = round(current_stats.off_steals / current_stats.games, 1) if current_stats.off_steals else None
            context['current_bpg'] = round(current_stats.off_blocks / current_stats.games, 1) if current_stats.off_blocks else None
            context['current_opp_ppg'] = round(current_stats.opp_points / current_stats.games, 1) if current_stats.opp_points else None
            context['current_margin'] = round((current_stats.off_points - current_stats.opp_points) / current_stats.games, 1) if current_stats.off_points and current_stats.opp_points else None
            context['current_to_ratio'] = round(current_stats.off_turnover_ratio * 100, 1) if current_stats.off_turnover_ratio else None

        context['wins'] = json.dumps(wins)
        context['losses'] = json.dumps(losses)
        context['win_pct'] = json.dumps(win_pct)
        context['off_rtg'] = json.dumps(off_rating)
        context['opp_rtg'] = json.dumps(opp_rating)

        context['eff_fg'] = json.dumps(off_eff_fg_pct)
        context['to_ratio'] = json.dumps(off_to_ratio)
        context['oreb_pct'] = json.dumps(off_oreb_pct)
        context['ft_rate'] = json.dumps(off_ft_rate)

        context['off_fg_pct'] = json.dumps(off_fg_pct)
        context['three_pt_pct'] = json.dumps(off_3pt_pct)
        context['off_ft_pct'] = json.dumps(off_ft_pct)
        context['off_pts'] = json.dumps(off_pts)
        context['opp_pts'] = json.dumps(opp_pts)
        return context

class UpcomingView(TemplateView):
    """
    Predictions page. Renders one of two views chosen by the ?view= GET param:

      ?view=calendar (default) — monthly calendar grid (predictions_calendar.html)
      ?view=list               — original head-to-head card grid (head_head.html)

    Both views share data prerequisites (season stats, predictions) but build
    different context dicts and use different templates. The view parameter is
    propagated into context as `view_mode` so each template can render the
    Calendar/List toggle button.

    ─── Calendar view (?view=calendar) ───
    Month-grid view of every game with prediction accuracy color-coding.

    URL params:
      ?year=YYYY  — calendar year to display (defaults to today's year)
      ?month=M    — month number 1-12 (defaults to current month)

    For each game on the calendar:
      • status='correct'      — game played, model picked the actual winner (green)
      • status='incorrect'    — game played, model picked the wrong team (red)
      • status='unplayed'     — game scheduled, not yet played (neutral)
      • status='no_prediction'— game played but stats were missing for prediction
                                (treated as unplayed/neutral in the UI)

    Day-overflow handling:
      Cells display at most CAL_PILL_CAP game pills. Days with more games get
      a "+N more" pill that opens a modal containing the full head-to-head
      matchup cards (matchup, prediction badge, box score) for every game
      on that day. modal_days carries the enriched data.

    ─── List view (?view=list) ───
    Original head-to-head card grid with two sub-modes (?mode=upcoming /
    ?mode=results) and date filters (?date=YYYY-MM-DD / ?date=all). Same
    accuracy banner as the calendar view. Pagination via ?page= when
    showing "All" completed games.

    Context variables:
      view_mode     — 'calendar' or 'list' (always present)

      Calendar mode:
        weeks       — list of weeks; each week is a list of 7 day-cells.
                      Each cell is {date, in_month, is_today, games,
                      visible_games (≤ pill_cap), overflow_count, modal_id}.
        pill_cap    — CAL_PILL_CAP (cells truncate visible pills at this count)
        modal_days  — list of {date, modal_id, total_games, games} for every
                      day with overflow.
        year, month, month_name, prev_year, prev_month, next_year, next_month
        season_year, is_current_month, weekday_labels

      List mode:
        mode        — 'upcoming' or 'results'
        games       — enriched list of dicts for the selected date/filter.
        all_games   — enriched list of ALL games (for cross-page search).
        show_all    — bool, True when ?date=all was requested.
        upcoming_dates — next 7 / last 7 day tabs depending on mode.
        selected_date — date currently displayed (None when show_all).
        page_obj    — paginator (results mode + show_all only).

      Shared:
        today, accuracy
    """

    # Maximum game pills shown directly inside a day cell.
    CAL_PILL_CAP = 5

    def get_template_names(self):
        if self._view_mode() == 'list':
            return ['opencourt/head_head.html']
        return ['opencourt/predictions_calendar.html']

    def _view_mode(self):
        """Return 'list' if ?view=list was requested, else 'calendar'."""
        return 'list' if self.request.GET.get('view') == 'list' else 'calendar'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['view_mode'] = self._view_mode()
        if context['view_mode'] == 'list':
            self._build_list_context(context)
        else:
            self._build_calendar_context(context)
        return context

    def _parse_year_month(self):
        """Parse ?year= and ?month= GET params, falling back to today."""
        today = date.today()
        try:
            year = int(self.request.GET.get('year', today.year))
        except (TypeError, ValueError):
            year = today.year
        try:
            month = int(self.request.GET.get('month', today.month))
            if not 1 <= month <= 12:
                raise ValueError
        except (TypeError, ValueError):
            month = today.month
        # Clamp year to a reasonable range so a hostile/malformed param
        # can't ask us to enumerate centuries.
        if not 1990 <= year <= 2100:
            year = today.year
        return year, month

    def _build_calendar_context(self, context):
        """Populate `context` with the data the calendar template needs."""
        today = date.today()
        year, month = self._parse_year_month()

        # Compute the season for the displayed month using the data's
        # ending-year convention (Game.season=2026 ↔ season_label='20252026'
        # = the 2025-26 season). Nov-Dec games belong to a season ending
        # NEXT calendar year, Jan-Jun games belong to a season ending THIS
        # calendar year. We compute from the selected month rather than
        # today so a viewer browsing back to Feb 2025 gets the 2024-25
        # season's stats prefetched (season=2025).
        #
        # This must match _current_season_year() — both views need to
        # resolve the same season for the same date so the prefetched
        # team stats line up and predictions agree across views.
        season_year = year + 1 if month >= 7 else year

        # Month boundaries for the games queryset. Use a half-open interval
        # [first_day, next_first) so we don't have to think about month length.
        first_day = date(year, month, 1)
        if month == 12:
            next_first = date(year + 1, 1, 1)
        else:
            next_first = date(year, month + 1, 1)

        # Pull every game in this month (scheduled, final, or otherwise).
        # We don't filter on status because we want to show both played and
        # unplayed games — color is decided per-game below.
        #
        # The team_stats prefetch loads each game's GameTeamStats rows so the
        # overflow modal can render real box scores (vs. just season averages)
        # for completed games — same shape as the old head_head.html cards.
        qs = (
            Game.objects
            .filter(start_date__date__gte=first_day,
                    start_date__date__lt=next_first)
            .select_related('home_team', 'away_team')
            .prefetch_related(
                Prefetch(
                    'home_team__season_stats',
                    queryset=TeamSeasonStats.objects.filter(season=season_year),
                    to_attr='_current_stats',
                ),
                Prefetch(
                    'away_team__season_stats',
                    queryset=TeamSeasonStats.objects.filter(season=season_year),
                    to_attr='_current_stats',
                ),
                Prefetch(
                    'team_stats',
                    queryset=GameTeamStats.objects.select_related('team'),
                ),
            )
            .order_by('start_date')
        )
        games_list = list(qs)

        # Run predictions for *every* game in one batched predict() call.
        # We predict on unplayed games too so the calendar can show who the
        # model thinks will win (neutral pill); just because a game is in the
        # future doesn't mean we shouldn't render the predicted favorite.
        pred_model = _get_predict_model()
        predictions = _batch_predict_home_wins(games_list, pred_model)

        # Per-game season-average helpers — same logic as the old head_head
        # template used so the modal cards look identical to the old page.
        def avg(stat_obj, field):
            if stat_obj is None:
                return None
            total = getattr(stat_obj, field, None)
            games_played = getattr(stat_obj, 'games', None)
            if total and games_played:
                return round(total / games_played, 1)
            return None

        def pct(stat_obj, field):
            if stat_obj is None:
                return None
            val = getattr(stat_obj, field, None)
            return round(val, 1) if val is not None else None

        # Group games by local date. start_date is a tz-aware datetime, so
        # we localize to the project's timezone to avoid having a 10pm ET
        # game show up on the next calendar day.
        games_by_day = defaultdict(list)
        for g in games_list:
            if not g.start_date:
                continue
            local_dt = timezone.localtime(g.start_date)
            d = local_dt.date()

            is_played = (g.status == 'final' and g.home_winner is not None)
            pred_home_win = predictions.get(g.id)  # bool or None

            # Decide the cell color:
            #   correct    — model agreed with the actual home/away winner
            #   incorrect  — model disagreed with the actual winner
            #   unplayed   — game still scheduled / hasn't finished
            #   no_prediction — game finished but feature stats were missing
            if is_played and pred_home_win is not None:
                actual_home_win = bool(g.home_winner)
                status = 'correct' if pred_home_win == actual_home_win else 'incorrect'
            elif is_played:
                status = 'no_prediction'
            else:
                status = 'unplayed'

            predicted_winner = None
            prediction_dict = None
            if pred_home_win is not None:
                predicted_winner = g.home_team if pred_home_win else g.away_team
                prediction_dict = {
                    'winner': predicted_winner,
                    'is_home_win': pred_home_win,
                }

            actual = None
            if is_played:
                actual = {
                    'winner': g.home_team if g.home_winner else g.away_team,
                    'home_points': g.home_points,
                    'away_points': g.away_points,
                }

            prediction_correct = None
            if prediction_dict and actual:
                prediction_correct = (prediction_dict['winner'].id == actual['winner'].id)

            # Per-game box score from the prefetch cache — rows are present
            # only for completed games. Modal cards fall back to season
            # averages when these are None (matching old head_head.html).
            home_game_stats = None
            away_game_stats = None
            for stat in g.team_stats.all():
                if stat.team_id == g.home_team_id:
                    home_game_stats = stat
                elif stat.team_id == g.away_team_id:
                    away_game_stats = stat

            h_stats = g.home_team.current_season
            a_stats = g.away_team.current_season

            games_by_day[d].append({
                'game': g,
                'home_team': g.home_team,
                'away_team': g.away_team,
                'status': status,
                'predicted_winner': predicted_winner,
                'prediction': prediction_dict,
                'actual': actual,
                'prediction_correct': prediction_correct,
                'home_game_stats': home_game_stats,
                'away_game_stats': away_game_stats,
                'home_stats': {
                    'pts': avg(h_stats, 'off_points'),
                    'fgp': pct(h_stats, 'off_fg_pct'),
                    'tpp': pct(h_stats, 'off_3pt_pct'),
                    'ftp': pct(h_stats, 'off_ft_pct'),
                    'reb': avg(h_stats, 'off_reb_total'),
                    'oreb': avg(h_stats, 'off_reb_offensive'),
                    'ast': avg(h_stats, 'off_assists'),
                    'stl': avg(h_stats, 'off_steals'),
                    'blk': avg(h_stats, 'off_blocks'),
                    'tov': avg(h_stats, 'off_turnovers'),
                },
                'away_stats': {
                    'pts': avg(a_stats, 'off_points'),
                    'fgp': pct(a_stats, 'off_fg_pct'),
                    'tpp': pct(a_stats, 'off_3pt_pct'),
                    'ftp': pct(a_stats, 'off_ft_pct'),
                    'reb': avg(a_stats, 'off_reb_total'),
                    'oreb': avg(a_stats, 'off_reb_offensive'),
                    'ast': avg(a_stats, 'off_assists'),
                    'stl': avg(a_stats, 'off_steals'),
                    'blk': avg(a_stats, 'off_blocks'),
                    'tov': avg(a_stats, 'off_turnovers'),
                },
                'start_local': local_dt,
                'home_points': g.home_points,
                'away_points': g.away_points,
                'is_played': is_played,
            })

        # Build the 6×7 (give or take) calendar grid. monthdatescalendar()
        # pads the first/last weeks with days from adjacent months so each
        # row is always 7 cells. firstweekday=6 = Sunday-first.
        #
        # Each cell carries:
        #   games            — full list of game items for the day
        #   visible_games    — first CAL_PILL_CAP items, rendered as pills in-cell
        #   overflow_count   — count of games hidden behind the "+N more" pill
        #   modal_id         — DOM id of this day's overflow modal (only used
        #                       when overflow_count > 0; deterministic so the
        #                       template can reference it without extra ctx)
        cal = calendar.Calendar(firstweekday=6)
        pill_cap = self.CAL_PILL_CAP
        weeks = []
        modal_days = []
        for week in cal.monthdatescalendar(year, month):
            week_cells = []
            for d in week:
                day_games = games_by_day.get(d, [])
                overflow = max(0, len(day_games) - pill_cap)
                modal_id = f'day-modal-{d.isoformat()}'
                week_cells.append({
                    'date': d,
                    'in_month': d.month == month,
                    'is_today': d == today,
                    'games': day_games,
                    'visible_games': day_games[:pill_cap],
                    'overflow_count': overflow,
                    'modal_id': modal_id,
                })
                # Build modals only for in-month days that overflow. Out-of-
                # month padding shouldn't generate modals — those games will
                # show up properly when the user navigates to that month.
                if overflow > 0 and d.month == month:
                    modal_days.append({
                        'date': d,
                        'modal_id': modal_id,
                        'total_games': len(day_games),
                        'games': day_games,
                    })
            weeks.append(week_cells)

        # Prev / next month navigation. Roll year over at the boundaries.
        prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
        next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)

        # Season-wide accuracy banner (cached). The CacheWarmerMiddleware
        # populates this in the background on first request, so reading from
        # the cache is the fast path. If the cache is empty (e.g. a cold
        # worker), fall back to a synchronous compute — same logic the old
        # results page used.
        current_season_year = _current_season_year()
        accuracy_key = ACCURACY_CACHE_KEY.format(season_year=current_season_year)
        season_accuracy = cache.get(accuracy_key)
        if season_accuracy is None:
            season_accuracy = _warm_season_accuracy(current_season_year)

        context.update({
            'weeks': weeks,
            'modal_days': modal_days,
            'pill_cap': pill_cap,
            'year': year,
            'month': month,
            'month_name': calendar.month_name[month],
            'prev_year': prev_year,
            'prev_month': prev_month,
            'next_year': next_year,
            'next_month': next_month,
            'today': today,
            'season_year': season_year,
            'is_current_month': (year == today.year and month == today.month),
            'accuracy': season_accuracy,
            'weekday_labels': ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
        })

    def _build_list_context(self, context):
        """Populate `context` for the original head-to-head list view.

        This is the pre-calendar logic restored verbatim — see the docstring
        on UpcomingView for the URL params and context variable contract.
        """
        today = date.today()
        tomorrow = today + timedelta(days=1)

        # Season field stores the starting year. Games from Nov-Dec use the
        # same year, games from Jan-Jun are year-1. We use the shared
        # _current_season_year() helper so the list view's prefetched
        # season stats line up with the calendar view's — otherwise the
        # same game's prediction features differ between views and can
        # show as "correct" in one and "incorrect" in the other.
        season_year = _current_season_year()

        # Timezone-aware "start of today" for DateTimeField comparisons.
        today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))

        # Sub-mode: upcoming (default) vs. results.
        mode = self.request.GET.get('mode', 'upcoming')
        if mode not in ('upcoming', 'results'):
            mode = 'upcoming'
        results_mode = (mode == 'results')

        # Date tabs: next 7 days for upcoming, last 7 days for results.
        if results_mode:
            upcoming_dates = [today - timedelta(days=i) for i in range(7)]
        else:
            upcoming_dates = [today + timedelta(days=i) for i in range(7)]

        # Determine whether "Show All" was requested. Results mode defaults
        # to "all" when no date param is given.
        date_param = self.request.GET.get('date', 'all' if results_mode else str(today))
        show_all = (date_param == 'all')

        if show_all:
            selected_date = None
        else:
            try:
                selected_date = date.fromisoformat(date_param)
            except ValueError:
                selected_date = today

        # ── Single season-wide queryset ─────────────────────────────────
        # We pull EVERY game in the current season (scheduled + final) once,
        # enrich it once, and use the enriched list for both the visible
        # cards (filtered + paginated by mode) and the global search pool
        # rendered into the search-results panel. The big win: the search
        # bar finds any game the user types — past or future — without
        # being limited to whatever 50 cards happen to be on the current
        # paginated page. The trade-off is one heavier server pass instead
        # of the previous "small visible queryset + small pool" approach.
        season_qs = (
            Game.objects
            .filter(season=season_year)
            .select_related('home_team', 'away_team')
            .prefetch_related(
                Prefetch(
                    'home_team__season_stats',
                    queryset=TeamSeasonStats.objects.filter(season=season_year),
                    to_attr='_current_stats',
                ),
                Prefetch(
                    'away_team__season_stats',
                    queryset=TeamSeasonStats.objects.filter(season=season_year),
                    to_attr='_current_stats',
                ),
                Prefetch(
                    'team_stats',
                    queryset=GameTeamStats.objects.select_related('team'),
                ),
            )
            .order_by('start_date')  # ascending; we reverse for results display below
        )
        season_games = list(season_qs)

        # Per-game average helpers.
        def avg(stat_obj, field):
            if stat_obj is None:
                return None
            total = getattr(stat_obj, field, None)
            games_played = getattr(stat_obj, 'games', None)
            if total and games_played:
                return round(total / games_played, 1)
            return None

        def pct(stat_obj, field):
            if stat_obj is None:
                return None
            val = getattr(stat_obj, field, None)
            return round(val, 1) if val is not None else None

        # Load the prediction model once and run a single batched predict()
        # over the entire season. This is the key perf move — XGBoost has
        # ~5-50ms of fixed overhead per call, so the previous per-game loop
        # would have timed out on a 7000+ game season. _batch_predict_home_wins
        # builds one DataFrame and returns {game_id: predicted_home_win bool}.
        pred_model = _get_predict_model()
        predictions = _batch_predict_home_wins(season_games, pred_model)

        def enrich_one(game):
            h_stats = game.home_team.current_season
            a_stats = game.away_team.current_season

            is_home_win = predictions.get(game.id)
            prediction = None
            if is_home_win is not None:
                prediction = {
                    'winner': game.home_team if is_home_win else game.away_team,
                    'is_home_win': is_home_win,
                }

            # `actual` is meaningful only for completed games. The earlier
            # `if (game.home_winner and game.away_winner) is not None` is a
            # truthiness bug that misses False winners; this version is
            # correct.
            actual = None
            if game.home_winner is not None and game.away_winner is not None:
                actual = {
                    'winner': game.home_team if game.home_winner else game.away_team,
                    'home_points': game.home_points,
                    'away_points': game.away_points,
                }

            prediction_correct = None
            if prediction and actual:
                prediction_correct = (prediction['winner'].id == actual['winner'].id)

            home_game_stats = None
            away_game_stats = None
            for stat in game.team_stats.all():
                if stat.team_id == game.home_team_id:
                    home_game_stats = stat
                elif stat.team_id == game.away_team_id:
                    away_game_stats = stat

            return {
                'game': game,
                'home_team': game.home_team,
                'away_team': game.away_team,
                'prediction': prediction,
                'actual': actual,
                'prediction_correct': prediction_correct,
                'home_game_stats': home_game_stats,
                'away_game_stats': away_game_stats,
                'home_stats': {
                    'pts': avg(h_stats, 'off_points'),
                    'fgp': pct(h_stats, 'off_fg_pct'),
                    'tpp': pct(h_stats, 'off_3pt_pct'),
                    'ftp': pct(h_stats, 'off_ft_pct'),
                    'reb': avg(h_stats, 'off_reb_total'),
                    'oreb': avg(h_stats, 'off_reb_offensive'),
                    'ast': avg(h_stats, 'off_assists'),
                    'stl': avg(h_stats, 'off_steals'),
                    'blk': avg(h_stats, 'off_blocks'),
                    'tov': avg(h_stats, 'off_turnovers'),
                },
                'away_stats': {
                    'pts': avg(a_stats, 'off_points'),
                    'fgp': pct(a_stats, 'off_fg_pct'),
                    'tpp': pct(a_stats, 'off_3pt_pct'),
                    'ftp': pct(a_stats, 'off_ft_pct'),
                    'reb': avg(a_stats, 'off_reb_total'),
                    'oreb': avg(a_stats, 'off_reb_offensive'),
                    'ast': avg(a_stats, 'off_assists'),
                    'stl': avg(a_stats, 'off_steals'),
                    'blk': avg(a_stats, 'off_blocks'),
                    'tov': avg(a_stats, 'off_turnovers'),
                },
            }

        # Enrich the entire season once. This is the single source of
        # truth for everything below — visible cards AND the search pool.
        all_games = [enrich_one(g) for g in season_games]

        # Build the visible `games` list as a filter over the enriched pool.
        # We avoid running predictions twice by reusing the same dicts.
        if results_mode:
            # Only completed games with a known winner are eligible.
            finished = [
                item for item in all_games
                if item['game'].status == 'final' and item['game'].home_winner is not None
            ]
            # Results page lists most-recent-first.
            finished.sort(
                key=lambda item: item['game'].start_date or datetime.min,
                reverse=True,
            )

            if show_all:
                paginator = Paginator(finished, 50)
                page_number = self.request.GET.get('page', 1)
                page_obj = paginator.get_page(page_number)
                context['page_obj'] = page_obj
                games = list(page_obj.object_list)
            else:
                games = [
                    item for item in finished
                    if item['game'].start_date
                    and item['game'].start_date.date() == selected_date
                ]

            accuracy_key = ACCURACY_CACHE_KEY.format(season_year=season_year)
            season_accuracy = cache.get(accuracy_key)
            if season_accuracy is None:
                season_accuracy = _warm_season_accuracy(season_year)
            context['accuracy'] = season_accuracy
        else:
            # Upcoming = scheduled and not in the past.
            scheduled = [
                item for item in all_games
                if item['game'].status == 'scheduled'
                and item['game'].start_date
                and item['game'].start_date >= today_start
            ]
            # season_qs is already start_date ascending, so scheduled is too.

            if show_all:
                games = scheduled
            else:
                games = [
                    item for item in scheduled
                    if item['game'].start_date.date() == selected_date
                ]

        context.update({
            'mode': mode,
            'games': games,
            'all_games': all_games,
            'show_all': show_all,
            'upcoming_dates': upcoming_dates,
            'selected_date': selected_date,
            'today': today,
            'tomorrow': tomorrow,
        })
