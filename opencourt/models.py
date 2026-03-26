# models.py — Database models for the opencourt app.
#
# Models define the schema for every table in our SQLite database. Django's ORM
# maps each class to a table and each field to a column, so the Python you see
# here IS the source of truth for the DB schema.
#
# After adding or changing models, run:
#   python manage.py makemigrations   (generates a migration file describing the change)
#   python manage.py migrate          (applies the migration to the database)
#
# Relationships at a glance:
#   Conference  1 ── * Team  1 ── * TeamSeasonStats
#                      Team  1 ── * Game (home_games)
#                      Team  1 ── * Game (away_games)
#                      Team  1 ── * GameTeamStats (game_stats)
#                      Game  1 ── 2 GameTeamStats (team_stats)
#
#   conference.teams.all()          → all teams in a conference
#   team.conference                 → the conference a team belongs to
#   team.season_stats.all()         → every season row for a team
#   team.current_season             → shortcut property returning the latest season stats object
#   team.current_season.wins        → a specific stat field on that season
#   team.home_games.all()           → all games where this team was home
#   team.away_games.all()           → all games where this team was away
#   team.game_stats.all()           → all per-game box score rows for a team
#   game.home_team / game.away_team → the two teams in a game
#   game.team_stats.all()           → both teams' box scores for a game (2 rows)
#
# Data source:
#   All models are populated by management commands that call service functions
#   in services.py, which hit the CBBData API (https://cbbdata.asmith.uiuc.edu).
#   Sync order matters — foreign keys create dependencies:
#     1. conferences → 2. teams → 3. season_stats → 4. games → 5. game_team_stats

from django.db import models
from django.utils.text import slugify
from .stats import win_percentage, point_differential

class Team(models.Model):
  """
  Represents a single NCAA Division I men's basketball program.

  One row per school (e.g. Duke, Gonzaga). Populated by the `sync_teams`
  management command, which calls sync_teams() in services.py. That function
  pulls the current season's team roster from the CBBData API and upserts
  rows using update_or_create() keyed on source_id.

  Key relationships:
    team.conference             → Conference object (nullable — set after sync_conferences runs)
    team.season_stats.all()     → QuerySet of TeamSeasonStats across all synced seasons
    team.current_season         → property returning the most recent TeamSeasonStats object
    conference.teams.all()      → reverse lookup from Conference to all its Teams

  URL routing:
    Each team has a unique slug (e.g. "duke-blue-devils") auto-generated on
    first save from school + mascot. Used in URL patterns for the team detail
    page: /teams/<slug>/
  """

  # --- Primary key ---
  # BigAutoField lets Django manage the PK. We store the API's original ID
  # separately in source_id so we can match records during sync without
  # coupling our PK to an external system.
  id = models.BigAutoField(primary_key=True)
  source_id = models.IntegerField(null = True, blank = True)

  # --- Display / identity ---
  slug = models.SlugField(unique=True)                                      # URL-safe identifier, e.g. "duke-blue-devils"
  school = models.CharField(max_length=255)                                 # canonical name, e.g. "Duke"
  abbrv = models.CharField(max_length=255)                                  # short code, e.g. "DUKE"
  display_name = models.CharField(max_length=255)                           # full display, e.g. "Duke Blue Devils"
  short_display_name = models.CharField(max_length=255)                     # compact display, e.g. "Duke"
  mascot = models.CharField(max_length = 100, null = True, blank = True)    # e.g. "Blue Devils"

  # --- Branding ---
  # Hex color codes from the API (e.g. "#001A57"). Nullable because some
  # smaller programs don't have branding data. Useful for theming team
  # detail pages or chart accent colors.
  primary_color = models.CharField(max_length = 7, null = True, blank = True)
  secondary_color = models.CharField(max_length = 7, null = True, blank = True)

  # --- Venue / location ---
  # Represents the team's current home arena. These can change year-to-year
  # (e.g. arena renovations, relocations), so they reflect the most recent
  # sync rather than historical data.
  current_venue_id = models.IntegerField(null = True, blank = True)
  current_venue_name = models.CharField(max_length = 200, null = True, blank = True)  # e.g. "Cameron Indoor Stadium"
  current_city = models.CharField(max_length = 100, null = True, blank = True)
  current_state = models.CharField(max_length = 50, null = True, blank = True)

  # --- Conference linkage ---
  # api_conference_id stores the raw integer ID from the CBBData API. We keep
  # it separate because Django auto-creates a `conference_id` column for the
  # ForeignKey below, and reusing the same name would cause a collision.
  # During sync_teams(), we use api_conference_id to look up the matching
  # Conference object and set the FK.
  api_conference_id = models.IntegerField(null = True, blank = True)
  conference = models.ForeignKey(
    'Conference',
    null = True,
    blank = True,
    on_delete = models.SET_NULL,  # keep the team even if its conference is deleted
    related_name = 'teams',       # enables conference.teams.all()
  )

  @property
  def current_season(self):
    """
    Return the TeamSeasonStats object for the current (most recent) season, or None.

    This property supports two access patterns:
      1. Prefetched (efficient) — when the view uses:
           Prefetch('teams__season_stats', queryset=..., to_attr='_current_stats')
         the stats are already loaded in memory; no DB hit.
      2. Fallback (lazy) — if no prefetch was set up (e.g. Django shell, or a
         view that didn't optimize), it runs a single query to grab the most
         recent season by ordering descending.

    Template usage:
      {{ team.current_season.wins }}
      {{ team.current_season.off_rating }}
      {% if team.current_season %} ... {% endif %}
    """
    if hasattr(self, '_current_stats'):
      return self._current_stats[0] if self._current_stats else None
    return self.season_stats.order_by('-season').first()

  def save(self, *args, **kwargs):
    """
    Auto-generate a URL-safe slug on first save if one isn't set.

    Format: "{school}-{mascot}" → slugified, e.g. "Duke" + "Blue Devils" →
    "duke-blue-devils". Only runs when slug is empty, so manual overrides
    are preserved. The slug is used in URL routing (see urls.py).
    """
    if not self.slug:
      self.slug = slugify(f"{self.school}-{self.mascot}")
    super().save(*args, **kwargs)

  def __str__(self):
    return self.school

class Conference(models.Model):
  """
  Represents an NCAA Division I basketball conference (e.g. ACC, Big Ten, SEC).

  There are 34 D1 conferences as of 2025-26. Populated by the `sync_conferences`
  management command, which must run BEFORE sync_teams so that teams can be
  linked to their conference via ForeignKey.

  Key relationships:
    conference.teams.all()      → all Team objects in this conference
    team.conference              → the Conference a team belongs to

  URL routing:
    Each conference has a unique slug auto-generated from short_name
    (e.g. "acc", "big-ten"). Used in URL patterns for the conference
    detail page.
  """

  id = models.BigAutoField(primary_key=True)
  source_id = models.IntegerField(null = True, blank = True)    # original API ID, used for matching during sync
  slug = models.SlugField(unique=True)                          # URL-safe identifier, e.g. "big-ten"
  name = models.CharField(max_length=255)                       # full name, e.g. "Big Ten Conference"
  abbrv = models.CharField(max_length=255)                      # abbreviation, e.g. "B10"
  short_name = models.CharField(max_length=255)                 # display name, e.g. "Big Ten"

  def save(self, *args, **kwargs):
    """Auto-generate slug from short_name on first save (e.g. "Big Ten" → "big-ten")."""
    if not self.slug:
      self.slug = slugify(f"{self.short_name}")
    super().save(*args, **kwargs)

  def __str__(self):
    return self.abbrv

class TeamSeasonStats(models.Model):
  """
  Season-level aggregate statistics for a single team in a single year.

  One row per team per season (enforced by unique_together). Contains both
  offensive (off_) and opponent/defensive (opp_) stats stored flat so that
  dashboards and charts can compare them without joins.

  Populated by the `sync_season_stats` management command, which calls
  sync_all_season_stats() in services.py. That function fetches stats in
  bulk per-season (not per-team) to minimize API calls and avoid rate limits.
  Only the last ~20 seasons are synced (controlled by STATS_START_YEAR in
  services.py).

  Key relationships:
    stats.team                  → the Team this row belongs to
    team.season_stats.all()     → all seasons for a team (ordered newest-first by default)
    team.current_season         → property shortcut to the most recent season's stats

  Stats glossary:
    The "Four Factors" (Dean Oliver) are the most predictive indicators of
    team success in basketball. They're weighted roughly:
      1. Shooting  (40%) — off_eff_fg_pct: effective FG%, accounts for 3-pointers
                           being worth more. Formula: (FG + 0.5 * 3P) / FGA
      2. Turnovers (25%) — off_turnover_ratio: turnovers per 100 possessions.
                           Lower is better.
      3. Rebounding (20%) — off_oreb_pct: percentage of available offensive rebounds
                            grabbed. Higher means more second-chance points.
      4. Free throws (15%) — off_ft_rate: free throw attempts relative to field goal
                             attempts (FTA / FGA). Measures ability to get to the line.
    Source: https://www.basketball-reference.com/about/factors.html

    Efficiency ratings:
      off_rating — points scored per 100 possessions (offensive efficiency)
      opp_rating — points allowed per 100 possessions (defensive efficiency)
      These are tempo-independent, making them better for cross-team comparison
      than raw points. A good offense is ~110+, a good defense is ~95 or below.

    Pace:
      Possessions per 40 minutes. Affects raw counting stats (points, rebounds,
      etc.) but NOT efficiency ratings. Important for predicting game totals.

  Future:
    This model will serve as the primary feature source for the prediction
    model. The Four Factors + efficiency ratings are expected to be the
    strongest input features. Game-level data (not yet modeled) would further
    improve predictions by enabling matchup-specific features.
  """

  # --- Identity ---
  team = models.ForeignKey(
    'Team',
    on_delete = models.CASCADE,     # if a team is deleted, remove all its stats too
    related_name = 'season_stats',  # enables team.season_stats.all()
  )
  season = models.IntegerField()                    # the starting year of the season, e.g. 2024 means the 2024-25 season
  season_label = models.CharField(max_length = 20)  # human-readable label, e.g. "2024-25"

  # --- Game totals ---
  games = models.IntegerField(null = True, blank = True)
  wins = models.FloatField(null = True, blank = True)     # float because API returns float
  losses = models.FloatField(null = True, blank = True)
  win_pct = models.FloatField(null = True, blank = True)  # auto-calculated in save(), stored as 0-100

  # --- Pace / tempo ---
  pace = models.FloatField(null = True, blank = True)           # possessions per 40 min — avg is ~68
  total_minutes = models.FloatField(null = True, blank = True)  # total team minutes played in the season

  # --- Offensive shooting ---
  # Raw makes, attempts, and percentages for each shot type.
  # Percentages are stored as decimals (e.g. 0.45 = 45%).
  off_fg_made = models.FloatField(null = True, blank = True)
  off_fg_attempted = models.FloatField(null = True, blank = True)
  off_fg_pct = models.FloatField(null = True, blank = True)

  off_2pt_made = models.FloatField(null = True, blank = True)
  off_2pt_attempted = models.FloatField(null = True, blank = True)
  off_2pt_pct = models.FloatField(null = True, blank = True)

  off_3pt_made = models.FloatField(null = True, blank = True)
  off_3pt_attempted = models.FloatField(null = True, blank = True)
  off_3pt_pct = models.FloatField(null = True, blank = True)

  off_ft_made = models.FloatField(null = True, blank = True)
  off_ft_attempted = models.FloatField(null = True, blank = True)
  off_ft_pct = models.FloatField(null = True, blank = True)

  # --- Offensive counting stats (season totals) ---
  off_points = models.FloatField(null = True, blank = True)
  off_assists = models.FloatField(null = True, blank = True)
  off_steals = models.FloatField(null = True, blank = True)
  off_blocks = models.FloatField(null = True, blank = True)
  off_turnovers = models.FloatField(null = True, blank = True)

  # --- Offensive rebounds (season totals) ---
  off_reb_total = models.FloatField(null = True, blank = True)       # total rebounds
  off_reb_offensive = models.FloatField(null = True, blank = True)   # offensive boards only
  off_reb_defensive = models.FloatField(null = True, blank = True)   # defensive boards only

  # --- Offensive Four Factors + advanced metrics ---
  # These are the core analytics features. See docstring above for definitions.
  off_eff_fg_pct = models.FloatField(null = True, blank = True)      # effective FG% — (FG + 0.5 * 3P) / FGA
  off_ft_rate = models.FloatField(null = True, blank = True)         # FTA / FGA — ability to get to the free throw line
  off_oreb_pct = models.FloatField(null = True, blank = True)        # offensive rebound % — second-chance opportunities
  off_turnover_ratio = models.FloatField(null = True, blank = True)  # turnovers per 100 possessions — ball security
  off_true_shooting = models.FloatField(null = True, blank = True)   # TS% — overall shooting efficiency including FTs and 3s
  off_rating = models.FloatField(null = True, blank = True)          # points per 100 possessions — THE key offensive metric
  off_possessions = models.FloatField(null = True, blank = True)     # total possessions in the season

  # --- Opponent / defensive stats ---
  # Mirror of the offensive stats, but measuring what the OPPONENT did against
  # this team. Lower values generally mean better defense. The opp_ prefix
  # fields use the same definitions as their off_ counterparts.
  opp_fg_pct = models.FloatField(null = True, blank = True)
  opp_2pt_pct = models.FloatField(null = True, blank = True)
  opp_3pt_pct = models.FloatField(null = True, blank = True)
  opp_ft_pct = models.FloatField(null = True, blank = True)
  opp_points = models.FloatField(null = True, blank = True)
  opp_assists = models.FloatField(null = True, blank = True)
  opp_turnovers = models.FloatField(null = True, blank = True)
  opp_reb_total = models.FloatField(null = True, blank = True)
  opp_reb_offensive = models.FloatField(null = True, blank = True)
  opp_eff_fg_pct = models.FloatField(null = True, blank = True)
  opp_ft_rate = models.FloatField(null = True, blank = True)
  opp_turnover_ratio = models.FloatField(null = True, blank = True)
  opp_true_shooting = models.FloatField(null = True, blank = True)
  opp_rating = models.FloatField(null = True, blank = True)          # defensive rating — points allowed per 100 possessions

  def save(self, *args, **kwargs):
    """Auto-calculate win_pct before every save using the win_percentage() helper from stats.py."""
    self.win_pct = win_percentage(self.wins, self.losses)
    super().save(*args, **kwargs)

  @property
  def point_margin(self):
    """Returns the point margin for this season (off_points - opp_points)."""
    if self.off_points is None or self.opp_points is None:
      return None
    return point_differential(self.off_points, self.opp_points)

  class Meta:
    unique_together = ('team', 'season')
    ordering = ['-season']

  def __str__(self):
    return f"{self.team} — {self.season_label}"

class Game(models.Model):
  """
  A single completed or scheduled game between two teams.

  One row per game. Populated from the CBBData /games endpoint, which
  provides the matchup metadata, final scores, venue, and Elo ratings.
  This is the "schedule row" — what you'd see in a team's season schedule
  table (date, opponent, score, W/L).

  Key relationships:
    game.home_team                → Team object for the home side
    game.away_team                → Team object for the away side
    team.home_games.all()         → all games where this team was home
    team.away_games.all()         → all games where this team was away
    game.team_stats.all()         → GameTeamStats rows (2 per game, one per team)

  The /games endpoint returns one row per game with both teams' info
  flattened (homeTeam/awayTeam, homePoints/awayPoints). We store both
  FKs so you can query from either team's perspective.

  Elo ratings:
    homeTeamEloStart/End and awayTeamEloStart/End track each team's Elo
    before and after the game. Useful for strength-of-schedule analysis
    and as a potential feature for the prediction model.

  Sync: populated by sync_games() in services.py via the `sync_games`
  management command. The API caps at 3,000 games per request, so the
  fetch is split into monthly date-range windows (Nov → May) to capture
  the full ~5,500-game season including postseason tournaments.
  """

  # --- Identity ---
  id = models.BigAutoField(primary_key=True)
  source_id = models.CharField(max_length=50, null=True, blank=True)   # API's string ID for this game
  season = models.IntegerField()                                       # e.g. 2025 for the 2025-26 season
  season_label = models.CharField(max_length=20)                       # e.g. "2025-26"
  season_type = models.CharField(max_length=20, null=True, blank=True) # "regular", "postseason"
  tournament = models.CharField(max_length=100, null=True, blank=True) # e.g. "NCAA Tournament", "NIT"
  game_type = models.CharField(max_length=50, null=True, blank=True)
  game_notes = models.TextField(null=True, blank=True)
  status = models.CharField(max_length=20, null=True, blank=True)      # "scheduled", "completed", "canceled"

  # --- Date / time ---
  start_date = models.DateTimeField(null=True, blank=True)
  start_time_tbd = models.BooleanField(default=False)

  # --- Home team ---
  home_team = models.ForeignKey(
    'Team',
    on_delete=models.CASCADE,
    related_name='home_games',   # team.home_games.all()
    null=True, blank=True,
  )
  home_conference = models.ForeignKey(
    'Conference',
    on_delete=models.SET_NULL,
    related_name='+',            # no reverse lookup needed
    null=True, blank=True,
  )
  home_seed = models.IntegerField(null=True, blank=True)         # tournament seed, if applicable
  home_points = models.IntegerField(null=True, blank=True)
  home_period_points = models.JSONField(null=True, blank=True)   # list of ints, e.g. [35, 43]
  home_winner = models.BooleanField(null=True, blank=True)
  home_elo_start = models.FloatField(null=True, blank=True)      # Elo rating entering the game
  home_elo_end = models.FloatField(null=True, blank=True)        # Elo rating after the game

  # --- Away team ---
  away_team = models.ForeignKey(
    'Team',
    on_delete=models.CASCADE,
    related_name='away_games',   # team.away_games.all()
    null=True, blank=True,
  )
  away_conference = models.ForeignKey(
    'Conference',
    on_delete=models.SET_NULL,
    related_name='+',
    null=True, blank=True,
  )
  away_seed = models.IntegerField(null=True, blank=True)
  away_points = models.IntegerField(null=True, blank=True)
  away_period_points = models.JSONField(null=True, blank=True)
  away_winner = models.BooleanField(null=True, blank=True)
  away_elo_start = models.FloatField(null=True, blank=True)
  away_elo_end = models.FloatField(null=True, blank=True)

  # --- Venue / context ---
  neutral_site = models.BooleanField(default=False)
  conference_game = models.BooleanField(default=False)           # was this an in-conference matchup?
  attendance = models.IntegerField(null=True, blank=True)
  venue_id = models.IntegerField(null=True, blank=True)
  venue = models.CharField(max_length=200, null=True, blank=True)
  city = models.CharField(max_length=100, null=True, blank=True)
  state = models.CharField(max_length=50, null=True, blank=True)

  # --- Analytics ---
  excitement = models.FloatField(null=True, blank=True)          # API-computed excitement index

  class Meta:
    ordering = ['-start_date']       # most recent games first
    indexes = [
      models.Index(fields=['season', 'home_team']),
      models.Index(fields=['season', 'away_team']),
    ]

  def __str__(self):
    return f"{self.home_team} vs {self.away_team} — {self.season_label}"

class GameTeamStats(models.Model):
  """
  Per-team box score stats for a single game.

  Two rows per game — one for each team. Populated from the CBBData
  /games/teams endpoint, which returns one row per team per game with
  the full stat breakdown (shooting, four factors, rebounds, etc.).

  Key relationships:
    stat.game                   → the Game this row belongs to
    stat.team                   → the Team this row is for
    game.team_stats.all()       → both teams' stats for this game
    team.game_stats.all()       → all game-level stats for a team

  The field structure intentionally mirrors TeamSeasonStats so that
  template code and chart configs can be reused across season-level
  and game-level views with minimal changes.

  The /games/teams endpoint also returns some matchup metadata (opponent,
  isHome, etc.) which overlaps with the Game model. We store those on
  Game and only keep the stat fields here to avoid duplication.

  Sync: populated by sync_game_team_stats() in services.py, which runs
  after sync_games() as part of `python manage.py sync_games`. The API
  returns 2 rows per game (one per team) and caps at 3,000 rows per
  request, so fetches are split into monthly windows. Keyed on
  (game, team) via unique_together to prevent duplicate rows on re-sync.
  """

  # --- Identity ---
  game = models.ForeignKey(
    'Game',
    on_delete=models.CASCADE,
    related_name='team_stats',   # game.team_stats.all()
  )
  team = models.ForeignKey(
    'Team',
    on_delete=models.CASCADE,
    related_name='game_stats',   # team.game_stats.all()
  )
  is_home = models.BooleanField(default=True)   # was this team the home team in this game?

  # --- Pace / tempo ---
  game_minutes = models.FloatField(null=True, blank=True)
  pace = models.FloatField(null=True, blank=True)              # possessions per 40 min for this game
  possessions = models.FloatField(null=True, blank=True)

  # --- Shooting ---
  fg_made = models.FloatField(null=True, blank=True)
  fg_attempted = models.FloatField(null=True, blank=True)
  fg_pct = models.FloatField(null=True, blank=True)

  two_pt_made = models.FloatField(null=True, blank=True)
  two_pt_attempted = models.FloatField(null=True, blank=True)
  two_pt_pct = models.FloatField(null=True, blank=True)

  three_pt_made = models.FloatField(null=True, blank=True)
  three_pt_attempted = models.FloatField(null=True, blank=True)
  three_pt_pct = models.FloatField(null=True, blank=True)

  ft_made = models.FloatField(null=True, blank=True)
  ft_attempted = models.FloatField(null=True, blank=True)
  ft_pct = models.FloatField(null=True, blank=True)

  # --- Counting stats ---
  points = models.IntegerField(null=True, blank=True)
  assists = models.IntegerField(null=True, blank=True)
  steals = models.IntegerField(null=True, blank=True)
  blocks = models.IntegerField(null=True, blank=True)
  turnovers = models.IntegerField(null=True, blank=True)
  team_turnovers = models.IntegerField(null=True, blank=True)   # team-level TOs (shot clock, etc.)

  # --- Rebounds ---
  reb_total = models.IntegerField(null=True, blank=True)
  reb_offensive = models.IntegerField(null=True, blank=True)
  reb_defensive = models.IntegerField(null=True, blank=True)

  # --- Fouls ---
  fouls_total = models.IntegerField(null=True, blank=True)
  fouls_technical = models.IntegerField(null=True, blank=True)
  fouls_flagrant = models.IntegerField(null=True, blank=True)

  # --- Points breakdown ---
  points_fast_break = models.IntegerField(null=True, blank=True)
  points_off_turnovers = models.IntegerField(null=True, blank=True)
  points_in_paint = models.IntegerField(null=True, blank=True)
  points_by_period = models.JSONField(null=True, blank=True)     # list of ints per half/OT
  largest_lead = models.IntegerField(null=True, blank=True)

  # --- Four Factors (game-level) ---
  # Same metrics as TeamSeasonStats but for a single game.
  eff_fg_pct = models.FloatField(null=True, blank=True)         # effective FG%
  ft_rate = models.FloatField(null=True, blank=True)            # FTA / FGA
  oreb_pct = models.FloatField(null=True, blank=True)           # offensive rebound %
  turnover_ratio = models.FloatField(null=True, blank=True)     # turnovers per 100 possessions

  # --- Advanced ---
  rating = models.FloatField(null=True, blank=True)             # offensive rating for this game
  true_shooting = models.FloatField(null=True, blank=True)      # TS%
  game_score = models.FloatField(null=True, blank=True)         # composite game score metric

  class Meta:
    unique_together = ('game', 'team')  # one stat row per team per game
    ordering = ['-game__start_date']

  def __str__(self):
    return f"{self.team} — Game {self.game_id}"
  
class Ranking(models.Model):
  """
  A single team's ranking in a poll for a specific week and season.

  One row per team per poll per week. Populated by the `sync_rankings`
  management command. Keyed on (season, season_type, week, poll_type, team)
  via unique_together to prevent duplicate rows on re-sync.
  """

  team = models.ForeignKey(
    'Team',
    on_delete=models.CASCADE,
    related_name='rankings',    # team.rankings.all()
    null=True, blank=True,
  )
  season = models.IntegerField()
  season_type = models.CharField(max_length=50, null=True, blank=True)   # "regular", "postseason"
  week = models.IntegerField(null=True, blank=True)
  poll_date = models.DateTimeField(null=True, blank=True)
  poll_type = models.CharField(max_length=100, null=True, blank=True)    # e.g. "AP", "Coaches"
  conference = models.ForeignKey(
    'Conference',
    on_delete=models.SET_NULL,
    related_name='+',
    null=True, blank=True,
  )
  ranking = models.IntegerField(null=True, blank=True)
  points = models.IntegerField(null=True, blank=True)
  first_place_votes = models.IntegerField(null=True, blank=True)

  class Meta:
    unique_together = ('season', 'season_type', 'week', 'poll_type', 'team')
    ordering = ['-season', '-week', 'ranking']

  def __str__(self):
    return f"{self.team} — #{self.ranking} ({self.poll_type}, Week {self.week}, {self.season})"
