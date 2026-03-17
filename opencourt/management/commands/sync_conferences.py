# sync_conferences.py — Management command for syncing conference data only.
#
# Fetches all conferences from the CBBData API and upserts them into the
# Conference model. Also links each team's conference FK using api_conference_id.
#
# Usage: python manage.py sync_conferences
from django.core.management.base import BaseCommand
from opencourt.services import sync_conferences

class Command(BaseCommand):
  help = 'Sync conference data from the CBBData API'

  def handle(self, *args, **options):
    self.stdout.write(self.style.HTTP_INFO('Syncing conferences...'))
    sync_conferences()
    self.stdout.write(self.style.SUCCESS('Conference sync complete ✅'))
