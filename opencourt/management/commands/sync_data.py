# sync_data.py — Django management command for a full data sync.
#
# Orchestrates all three sync steps in dependency order:
#   1. sync_conferences — must run first (teams FK into conferences)
#   2. sync_teams       — must run before stats (stats FK into teams)
#   3. sync_season_stats — most API-intensive; run separately if rate-limited
#
# To run a single step without triggering rate limits on the others:
#   python manage.py sync_conferences
#   python manage.py sync_teams
#   python manage.py sync_season_stats
#
# Usage: python manage.py sync_data
# Requirement: CBB_API_KEY to be set in your .env file.
from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
  help = 'Run all sync steps: conferences → teams → season stats'

  def handle(self, *args, **options):
    call_command('sync_conferences')
    call_command('sync_teams')
    call_command('sync_season_stats')
