# views.py — View functions and classes for the opencourt app.
#
# Views receive HTTP requests and return HTTP responses.
# Wire each view up to a URL in opencourt/urls.py.
# Templates live in templates/opencourt/.

from django.views.generic import TemplateView, ListView
from opencourt.models import Team, Conference

class HomeView(TemplateView):
    """Renders the home page."""
    template_name = 'opencourt/home.html'

# Additional views will be defined here (e.g. TeamDetailView, ConferenceView)
class AboutView(TemplateView):
    """Renders the about page."""
    template_name = 'opencourt/about.html'

class TeamListView(ListView):
    """Renders the team list page."""
    model = Team
    template_name = 'opencourt/teams.html'

    def get_queryset(self):
      return Team.objects.all()

class ConferenceListView(ListView):
    """Renders the conference list page."""
    model = Conference
    # Uncomment when conference.html is created
    # template_name = 'opencourt/conferences.html'

    def get_queryset(self):
      return Conference.objects.all()
