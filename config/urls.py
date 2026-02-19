# urls.py — Project-level URL configuration for OpenCourt.
#
# This is the root URL file. Django checks here first for every incoming request.
# Add a path() entry here to include each app's own urls.py file.
# As new apps are added to the project, include their urls.py below.

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Django admin panel — available at /admin/ in the browser
    path('admin/', admin.site.urls),
    # django-browser-reload — handles the long-poll endpoint that triggers
    # automatic browser refreshes during development when CSS or templates change.
    # This URL is only active in DEBUG mode; it has no effect in production.
    path('__reload__/', include('django_browser_reload.urls')),
    # opencourt app — handles all main site routes
    path('', include('opencourt.urls')),
]
