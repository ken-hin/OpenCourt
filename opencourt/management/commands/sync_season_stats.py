# sync_season_stats.py — Management command for syncing season stats only.
#
# Fetches stats for all teams across the last 26 seasons from the CBBData API
# using one bulk request per season (26 calls total). Requires teams to already
# be synced so that the team FK can be resolved by school name.
#
# This is the most API-intensive command — run it on its own to avoid
# triggering rate limits alongside conference and team syncs.
#
# Usage: python manage.py sync_season_stats
from django.core.management.base import BaseCommand
from opencourt.services import sync_all_season_stats

class Command(BaseCommand):
  help = 'Sync season stats for all teams from the CBBData API'

  def handle(self, *args, **options):
    self.stdout.write(self.style.HTTP_INFO('Syncing season stats...'))
    sync_all_season_stats()
    self.stdout.write(self.style.SUCCESS('Season stats sync complete ✅'))
