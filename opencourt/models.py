# models.py — Database models for the opencourt app.
# Each model maps to a database table.
# After adding or changing models, run:
#   python manage.py makemigrations
#   python manage.py migrate

from django.db import models
from django.utils.text import slugify

class Team(models.Model):
  """
  Represents a single college basketball team (Division I).

  Populated by sync_teams() in services.py, which pulls data from the
  CBBData API and upserts rows using update_or_create(). The `id` field
  matches the API's primary key so lookups stay consistent across syncs.

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
  conference_id = models.IntegerField(null = True, blank = True)
  conference = models.CharField(max_length = 100, null = True, blank = True)

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
