# models.py — Database models for the opencourt app.
# Each model maps to a database table.
# After adding or changing models, run:
#   python manage.py makemigrations
#   python manage.py migrate

from django.db import models
from django.utils.text import slugify
from .stats import win_percentage, point_differential

class Team(models.Model):
  """
  Represents a single college basketball team (Division I).

  Populated by sync_teams() in services.py, which pulls data from the
  CBBData API and upserts rows using update_or_create(). The `id` field
  matches the API's primary key, so lookups stay consistent across syncs.

  URL-friendly slugs are auto-generated from school + mascot on first save
  (e.g. "duke-blue-devils") and used for team detail page URLs.
  """

  id = models.BigAutoField(primary_key=True)
  source_id = models.IntegerField(null = True, blank = True)
  slug = models.SlugField(unique=True)
  school = models.CharField(max_length=255)
  abbrv = models.CharField(max_length=255)
  display_name = models.CharField(max_length=255)
  short_display_name = models.CharField(max_length=255)
  mascot = models.CharField(max_length = 100, null = True, blank = True)
  primary_color = models.CharField(max_length = 7, null = True, blank = True)
  secondary_color = models.CharField(max_length = 7, null = True, blank = True)
  current_venue_id = models.IntegerField(null = True, blank = True)
  current_venue_name = models.CharField(max_length = 200, null = True, blank = True)
  current_city = models.CharField(max_length = 100, null = True, blank = True)
  current_state = models.CharField(max_length = 50, null = True, blank = True)
  # Raw integer ID from the CBBData API — kept for reference during syncs.
  # Django will create its own `conference_id` column for the ForeignKey below,
  # so this field is renamed to avoid a collision.
  api_conference_id = models.IntegerField(null = True, blank = True)
  # FK to the Conference model — null until sync_conferences() has run and
  # populated the conferences table. Use team.conference to get the full object,
  # team.conference_id for the FK integer, conference.teams.all() for the reverse.
  conference = models.ForeignKey(
    'Conference',
    null = True,
    blank = True,
    on_delete = models.SET_NULL,  # if a conference is deleted, don't delete its teams
    related_name = 'teams',       # enables conference.teams.all()
  )
  def save(self, *args, **kwargs):
    """
    Override save to auto-generate a URL slug on the first creation.

    Combines school name and mascot (e.g. "Duke" + "Blue Devils" →
    "duke-blue-devils"). Only runs when the slug is empty, so manually
    set slugs are preserved.
    """
    if not self.slug:
      self.slug = slugify(f"{self.school}-{self.mascot}")
    super().save(*args, **kwargs)

  def __str__(self):
    """Return the school name (e.g. 'Duke') for admin and shell display."""
    return self.school

class Conference(models.Model):

  id = models.BigAutoField(primary_key=True)
  source_id = models.IntegerField(null = True, blank = True)
  slug = models.SlugField(unique=True)
  name = models.CharField(max_length=255)
  abbrv = models.CharField(max_length=255)
  short_name = models.CharField(max_length=255)

  def save(self, *args, **kwargs):

    if not self.slug:
      self.slug = slugify(f"{self.short_name}")

    super().save(*args, **kwargs)

  def __str__(self):
    return self.abbrv

class TeamSeasonStats(models.Model) :
  """
  Season-level statistics for a single team, sourced from the CBBData API.
  Covers one row per team per season. Both offensive (off_) and opponent/
  defensive (opp_) stats are stored flat so dashboards can compare them
  without a join.

  Lookup key: (team, season) — enforced by unique_together below.
  Synced by sync_team_stats() in services.py.
  """

  # --- Identity ---
  team = models.ForeignKey('Team', on_delete = models.CASCADE, related_name = 'season_stats')
  season = models.IntegerField()  # e.g. 2024
  season_label = models.CharField(max_length = 20)  # e.g. "2024-25"

  # --- Game totals ---
  games = models.IntegerField(null = True, blank = True)
  wins = models.FloatField(null = True, blank = True)
  losses = models.FloatField(null = True, blank = True)
  win_pct = models.FloatField(null = True, blank = True)

  # --- Pace / tempo ---
  pace = models.FloatField(null = True, blank = True)  # possessions per 40 min
  total_minutes = models.FloatField(null = True, blank = True)

  # --- Offensive shooting ---
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

  # --- Offensive counting stats ---
  off_points = models.FloatField(null = True, blank = True)
  off_assists = models.FloatField(null = True, blank = True)
  off_steals = models.FloatField(null = True, blank = True)
  off_blocks = models.FloatField(null = True, blank = True)
  off_turnovers = models.FloatField(null = True, blank = True)

  # --- Offensive rebounds ---
  off_reb_total = models.FloatField(null = True, blank = True)
  off_reb_offensive = models.FloatField(null = True, blank = True)
  off_reb_defensive = models.FloatField(null = True, blank = True)

  # --- Offensive four factors (advanced) ---
  off_eff_fg_pct = models.FloatField(null = True, blank = True)  # effective FG%
  off_ft_rate = models.FloatField(null = True, blank = True)  # FT attempts / FG attempts
  off_oreb_pct = models.FloatField(null = True, blank = True)  # offensive rebound %
  off_turnover_ratio = models.FloatField(null = True, blank = True)  # turnovers per 100 possessions
  off_true_shooting = models.FloatField(null = True, blank = True)  # TS%
  off_rating = models.FloatField(null = True, blank = True)  # points per 100 possessions
  off_possessions = models.FloatField(null = True, blank = True)

  # --- Opponent / defensive stats (same shape, opp_ prefix) ---
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
  opp_rating = models.FloatField(null = True, blank = True)  # defensive rating

  def save(self, *args, **kwargs) :

    self.win_pct = win_percentage(self.wins, self.losses)
    super().save(*args, **kwargs)

  @property
  def point_margin(self):
    """Returns the point margin for this season (off_points - opp_points)."""
    if self.off_points is None or self.opp_points is None:
      return None
    return point_differential(self.off_points, self.opp_points)

  class Meta :
    unique_together = ('team', 'season')
    ordering = ['-season']

  def __str__(self) :
    return f"{self.team} — {self.season_label}"
