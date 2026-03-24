# sync_rankingss.py — Management command for syncing rankings stats only.
#
#
# Usage: python manage.py sync_rankings
from django.core.management.base import BaseCommand
from opencourt.services import sync_all_rankings

class Command(BaseCommand):
  help = 'Sync ranking stats for all teams from the CBBData API'

  def handle(self, *args, **options):
    self.stdout.write(self.style.HTTP_INFO('Syncing ranking stats...'))
    sync_all_rankings()
    self.stdout.write(self.style.SUCCESS('Season rank sync complete ✅'))