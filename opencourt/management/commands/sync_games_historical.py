# sync_games_historical.py — Management command for backfilling historical
# game data across the last 3 seasons.
#
# Runs the historical equivalents of steps 4 + 5 of the sync pipeline:
#   4. sync_games_historical()           — fetches game-level matchup data
#                                          (scores, venue, Elo) from /games
#                                          across GAMES_HISTORY_START_YEAR →
#                                          CURRENT_YEAR → populates Game model
#   5. sync_game_team_stats_historical() — fetches per-team box scores
#                                          (shooting, rebounds, Four Factors)
#                                          from /games/teams across the same
#                                          range → populates GameTeamStats model
#
# Both functions loop season-by-season and split each season into monthly
# date-range windows (Nov → May) to stay under the 3,000-row-per-request cap.
# See services/sync.py for full implementation details.
#
# ⚠️ This is a one-time backfill command. With 3 seasons × 7 monthly windows
# each, expect ~42 API calls minimum plus BETWEEN_CALLS_DELAY between each.
# For incremental daily updates to the current season, use `sync_games` (or the
# update_* functions) instead.
#
# Games must be synced before game team stats since GameTeamStats has a FK
# into Game (resolved via source_id). Both steps require teams and conferences
# to already be in the DB so that FK lookups by school name / abbreviation work.
#
# Dependency order for a full historical backfill:
#   sync_conferences → sync_teams → sync_games_historical
#
# Usage: python manage.py sync_games_historical
from django.core.management.base import BaseCommand
from opencourt.services import sync_games_historical, sync_game_team_stats_historical

class Command(BaseCommand):
  help = 'Backfill historical games and per-team box scores across the last 3 seasons from the CBBData API'

  def handle(self, *args, **options):
    # Step 4 (historical): Game-level data across every season in the history window
    self.stdout.write(self.style.HTTP_INFO('Syncing historical games (this may take several minutes)...'))
    sync_games_historical()
    self.stdout.write(self.style.SUCCESS('Historical games sync complete ✅'))

    # Step 5 (historical): Per-team box scores for every historical game
    # Depends on Game rows from step 4 existing so the FK can be resolved.
    self.stdout.write(self.style.HTTP_INFO('Syncing historical game team stats (this may take several minutes)...'))
    sync_game_team_stats_historical()
    self.stdout.write(self.style.SUCCESS('Historical game team stats sync complete ✅'))
