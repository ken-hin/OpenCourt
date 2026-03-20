# sync_games.py — Management command for syncing game data.
#
# Runs steps 4 + 5 of the sync pipeline together:
#   4. sync_games()           — fetches game-level matchup data (scores, venue, Elo)
#                               from /games endpoint → populates Game model
#   5. sync_game_team_stats() — fetches per-team box scores (shooting, rebounds,
#                               Four Factors) from /games/teams → populates
#                               GameTeamStats model
#
# Both functions fetch the current season only and split API calls into monthly
# date-range windows (Nov → May) to work around the 3,000-row-per-request cap.
# See services.py for full implementation details.
#
# Games must be synced before game team stats since GameTeamStats has a FK
# into Game (resolved via source_id). Both steps require teams and conferences
# to already be in the DB so that FK lookups by school name / abbreviation work.
#
# Dependency order for the full pipeline:
#   sync_conferences → sync_teams → sync_season_stats → sync_games
#
# This command is also called by sync_data (the "run everything" command).
#
# Usage: python manage.py sync_games
from django.core.management.base import BaseCommand
from opencourt.services import sync_games, sync_game_team_stats

class Command(BaseCommand):
  help = 'Sync current season games and per-team box scores from the CBBData API'

  def handle(self, *args, **options):
    # Step 4: Game-level data (matchup metadata, scores, venue, Elo ratings)
    self.stdout.write(self.style.HTTP_INFO('Syncing games...'))
    sync_games()
    self.stdout.write(self.style.SUCCESS('Games sync complete ✅'))

    # Step 5: Per-team box scores (shooting splits, Four Factors, points breakdown)
    # Depends on Game rows from step 4 existing so the FK can be resolved.
    self.stdout.write(self.style.HTTP_INFO('Syncing game team stats...'))
    sync_game_team_stats()
    self.stdout.write(self.style.SUCCESS('Game team stats sync complete ✅'))
