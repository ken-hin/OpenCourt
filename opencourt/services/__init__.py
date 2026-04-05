# services/__init__.py — Public API for the opencourt.services package.
#
# Re-exports every function that was previously importable from the
# monolithic opencourt/services.py so that existing code like:
#
#   from opencourt.services import sync_teams, update_games
#
# continues to work without changes.

from .sync import (                         # noqa: F401
    sync_teams,
    sync_conferences,
    sync_all_season_stats,
    sync_all_rankings,
    sync_games,
    sync_game_team_stats,
)

from .update import (                       # noqa: F401
    update_teams,
    update_season_stats,
    update_games,
    update_game_team_stats,
    update_rankings,
)

from .fetch import (                        # noqa: F401
    fetch_teams,
    fetch_conferences,
    fetch_season_stats_bulk,
    fetch_rankings_bulk,
    fetch_games_bulk,
    fetch_game_team_stats_bulk,
)
