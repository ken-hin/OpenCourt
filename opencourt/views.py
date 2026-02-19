# views.py — View functions and classes for the opencourt app.
#
# Views receive HTTP requests and return HTTP responses.
# Wire each view up to a URL in opencourt/urls.py.
# Templates live in templates/opencourt/.

from django.views.generic import TemplateView


class HomeView(TemplateView):
    """Renders the home page."""
    template_name = 'opencourt/home.html'

# Additional views will be defined here (e.g. TeamDetailView, ConferenceView)
