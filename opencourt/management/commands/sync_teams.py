# sync_teams.py — Management command for syncing team data only.
#
# Fetches all Division I teams from the CBBData API and upserts them into
# the Team model. Requires conferences to already be synced so that the
# conference FK can be linked via sync_conferences().
#
# Usage: python manage.py sync_teams
from django.core.management.base import BaseCommand
from opencourt.services import sync_teams

class Command(BaseCommand):
  help = 'Sync team data from the CBBData API'

  def handle(self, *args, **options):
    self.stdout.write(self.style.HTTP_INFO('Syncing teams...'))
    sync_teams()
    self.stdout.write(self.style.SUCCESS('Team sync complete ✅'))
