# sync_data.py — Django management command for syncing CBBData API data.
#
# Pulls team data from the CBBData API and
# upserts it into the local database. This is the primary way to populate
# and refresh the database — run it manually or on a cron schedule.
#
# Usage: python manage.py sync_data
# Requirement: CBB_API_KEY to be set in your .env file.

from django.core.management.base import BaseCommand
from opencourt.services import sync_teams

class Command(BaseCommand):
  help = 'Sync team and conference data from the CBBData API'

  def handle(self, *args, **options):
    self.stdout.write(self.style.HTTP_INFO('Syncing teams...'))
    sync_teams()
    self.stdout.write(self.style.SUCCESS('Team sync complete ✅'))

    # Uncomment when sync_conferences() is ready:
    # self.stdout.write('Syncing conferences...')
    # sync_conferences()
    # self.stdout.write(self.style.SUCCESS('Conference sync complete.'))
