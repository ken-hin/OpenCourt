# admin.py — Django admin registration for the opencourt app.
#
# Register models here to make them manageable through the Django admin panel.
# Access the admin panel at /admin/ when the dev server is running.
# Example: admin.site.register(Team)

from django.contrib import admin
from opencourt.models import Team, Conference, TeamSeasonStats, Game, GameTeamStats, Ranking

# Models will be registered here
admin.site.register(Team)
admin.site.register(Conference)
admin.site.register(TeamSeasonStats)
admin.site.register(Game)
admin.site.register(GameTeamStats)
admin.site.register(Ranking)
