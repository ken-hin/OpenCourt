# update_data.py — Django management command for incremental data updates.
#
# Lighter-weight alternative to sync_data. Instead of pulling entire seasons
# of historical data, this only fetches:
#   - Teams (full — cheap, one API call)
#   - Season stats for the current season only (one API call)
#   - Games from the last 30 days (one API call)
#   - Game team stats from the last 30 days (one API call)
#   - Rankings for the current season only (one API call)
#
# Total: ~5 API calls vs ~30+ for a full sync.
#
# Ideal for daily/weekly cron jobs to keep the DB current without hitting
# rate limits or waiting several minutes for a full sync.
#
# Usage: python manage.py update_data
# Requirement: CBB_API_KEY to be set in your .env file.
#              The DB must already be initialized via sync_data.
from django.core.management.base import BaseCommand
from opencourt.services import (
    update_teams,
    update_season_stats,
    update_games,
    update_game_team_stats,
    update_rankings,
)


class Command(BaseCommand):
    help = 'Incremental update: teams + current season stats + last 30 days of games + rankings'

    def handle(self, *args, **options):
        self.stdout.write(self.style.HTTP_INFO('Updating teams...'))
        update_teams()
        self.stdout.write(self.style.SUCCESS('Teams update complete.'))

        self.stdout.write(self.style.HTTP_INFO('Updating season stats (current season)...'))
        update_season_stats()
        self.stdout.write(self.style.SUCCESS('Season stats update complete.'))

        self.stdout.write(self.style.HTTP_INFO('Updating games (last 30 days)...'))
        update_games()
        self.stdout.write(self.style.SUCCESS('Games update complete.'))

        self.stdout.write(self.style.HTTP_INFO('Updating game team stats (last 30 days)...'))
        update_game_team_stats()
        self.stdout.write(self.style.SUCCESS('Game team stats update complete.'))

        self.stdout.write(self.style.HTTP_INFO('Updating rankings (current season)...'))
        update_rankings()
        self.stdout.write(self.style.SUCCESS('Rankings update complete.'))

        self.stdout.write(self.style.SUCCESS('\nAll updates complete.'))
