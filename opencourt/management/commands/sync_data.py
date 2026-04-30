# sync_data.py — Django management command for a full data sync.
#
# Orchestrates all sync steps in dependency order:
#   1. sync_conferences       — must run first (teams FK into conferences)
#   2. sync_teams             — must run before stats (stats FK into teams)
#   3. sync_season_stats      — most API-intensive; run separately if rate-limited
#   4. sync_games             — current-season games + box scores
#   5. sync_rankings          — weekly poll rankings
#
# With the --historical flag, also runs sync_games_historical after the
# current-season games step. This backfills the last 3 seasons of games and
# per-team box scores — a one-time operation that adds ~42 API calls, so it's
# off by default.
#
# To run a single step without triggering rate limits on the others:
#   python manage.py sync_conferences
#   python manage.py sync_teams
#   python manage.py sync_season_stats
#   python manage.py sync_games
#   python manage.py sync_games_historical
#   python manage.py sync_rankings
#
# Usage:
#   python manage.py sync_data                # daily/weekly sync (current season only)
#   python manage.py sync_data --historical   # full sync + 3-season game backfill
#
# Requirement: CBB_API_KEY to be set in your .env file.
from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
  help = 'Run all sync steps: conferences → teams → season stats → games → rankings (+ optional historical backfill)'

  def add_arguments(self, parser):
    parser.add_argument(
      '--historical',
      action='store_true',
      help='Also run sync_games_historical to backfill the last 3 seasons of game data.',
    )

  def handle(self, *args, **options):
    call_command('sync_conferences')
    call_command('sync_teams')
    call_command('sync_season_stats')
    call_command('sync_games')
    if options['historical']:
      call_command('sync_games_historical')
    call_command('sync_rankings')
